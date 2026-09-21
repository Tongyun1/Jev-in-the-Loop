"""Observed actions through one persistent Browser Harness CDP session.

Derived from browser-use/jev-ultrafast under the MIT License.
"""

import hashlib
import json
import sys
import time
from pathlib import Path

from browser_harness.admin import ensure_daemon
from browser_harness.helpers import cdp

READ_STATE = Path(__file__).with_name("snapshot.js").read_text()
MARKER = f"(() => {{ const state={READ_STATE}; return state?.marker ?? null; }})()"


class StalePage(ValueError):
    pass


class Browser:
    def __init__(self, url: str, *, visible: bool, viewport=None):
        ensure_daemon()
        self.visible = visible
        self.viewport = viewport
        self.owned_targets = set()
        self.target = cdp("Target.createTarget", url="about:blank", background=not visible)["targetId"]
        self.owned_targets.add(self.target)
        self.session = cdp("Target.attachToTarget", targetId=self.target, flatten=True)["sessionId"]
        self.configure_viewport()
        self.call("Emulation.setFocusEmulationEnabled", enabled=True)
        if visible:
            cdp("Target.activateTarget", targetId=self.target)
        navigation = self.call("Page.navigate", url=url)
        if navigation.get("errorText"):
            raise RuntimeError("Initial navigation failed")
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            try:
                state = self.evaluate("[location.href, document.readyState]")
                if state and state[0] != "about:blank" and state[1] != "loading":
                    return
            except StalePage:
                pass
            time.sleep(0.02)
        raise RuntimeError("Initial document did not become ready")

    def call(self, method, **params):
        return cdp(method, session_id=self.session, **params)

    def configure_viewport(self):
        if getattr(self, "viewport", None) is not None:
            self.call(
                "Emulation.setDeviceMetricsOverride",
                width=self.viewport.width,
                height=self.viewport.height,
                deviceScaleFactor=1,
                mobile=False,
            )

    def evaluate(self, expression):
        response = self.call("Runtime.evaluate", expression=expression, returnByValue=True)
        if response.get("exceptionDetails"):
            raise StalePage("Document changed during evaluation")
        return response.get("result", {}).get("value")

    def observe(self):
        self.follow_popup()
        if getattr(self, "after_input", None):
            action, self.after_input = self.after_input, None
            try:
                self.call(
                    "Runtime.evaluate",
                    expression="""(action => new Promise(resolve => {
                      const field=window.__jevFast?.nodes.get(action.node);
                      const autocomplete=action.kind==='fill' && field?.getAttribute('role')==='combobox';
                      let frames=0, stopped=false, changed=performance.now();
                      const observer=new MutationObserver(()=>{changed=performance.now()});
                      observer.observe(document,{subtree:true,childList:true,attributes:true,characterData:true});
                      let timer;
                      const finish=()=>{stopped=true;observer.disconnect();clearTimeout(timer);resolve()};
                      const busy=()=>action.kind==='click' && field?.isConnected &&
                        (field.matches(':disabled,[aria-busy="true"],[aria-disabled="true"]') ||
                         [...field.querySelectorAll('*')].some(e=>/loading|spinner/i.test(String(e.className))));
                      timer=setTimeout(finish,busy() ? 2000 : autocomplete ? 800 : 400);
                      const ready=()=>{
                        if (stopped) return;
                        const ids=(field?.getAttribute('aria-controls')||field?.getAttribute('aria-owns')||'')
                          .split(/\\s+/).filter(Boolean);
                        const roots=ids.length
                          ? ids.map(id=>document.getElementById(id)).filter(Boolean)
                          : [document];
                        const options=roots.flatMap(root=>[...root.querySelectorAll('[role="option"]')]);
                        if (++frames>=2 && !busy() && performance.now()-changed>=60 &&
                          document.readyState!=='loading' &&
                          !document.querySelector('[aria-busy="true"]') && (!autocomplete || options.some(e=>{
                          const r=e.getBoundingClientRect();
                          return r.width && r.height && r.bottom>0 && r.top<innerHeight &&
                            e.checkVisibility({checkOpacity:true,checkVisibilityCSS:true});
                        }))) finish();
                        else requestAnimationFrame(ready);
                      };
                      requestAnimationFrame(ready);
                    }))("""
                    + json.dumps(action)
                    + ")",
                    awaitPromise=True,
                    returnByValue=True,
                )
            except (RuntimeError, StalePage):
                pass
            self.follow_popup()
        for attempt in range(10):
            try:
                return browser_operation({"operation": "observe", "session": self.session})
            except StalePage:
                if attempt == 9:
                    raise
                time.sleep(0.02)
        raise StalePage("Page did not settle")

    def follow_popup(self):
        """Follow only new direct children of our current tab, never a user's other tabs."""
        children = [
            item
            for item in cdp("Target.getTargets")["targetInfos"]
            if item.get("type") == "page"
            and item.get("openerId") == self.target
            and item["targetId"] not in self.owned_targets
        ]
        if len(children) > 1:
            raise RuntimeError("Multiple new child tabs; cannot safely choose a popup")
        if not children:
            return
        self.target = children[0]["targetId"]
        self.owned_targets.add(self.target)
        self.session = cdp("Target.attachToTarget", targetId=self.target, flatten=True)["sessionId"]
        self.call("Emulation.setFocusEmulationEnabled", enabled=True)
        self.configure_viewport()
        if self.visible:
            cdp("Target.activateTarget", targetId=self.target)
        self.after_input = None
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            try:
                state = self.evaluate("[location.href, document.readyState]")
                if state and state[0] != "about:blank" and state[1] != "loading":
                    return
            except StalePage:
                pass
            time.sleep(0.05)
        raise RuntimeError("New child tab did not finish initial navigation")

    def fresh(self, page, action=None):
        if action is not None and action["kind"] in {"click", "select", "fill", "press"}:
            node = action["node"]
            if type(node) is not int:
                return False
            current = self.evaluate(
                "(() => { const c=window.__jevFast; "
                f"return c ? [c.pageKey(),c.guard(c.nodes.get({node}))] : null; }})()"
            )
            return current == [page["page_key"], page["guards"].get(str(node))]
        return self.evaluate(MARKER) == page["marker"]

    def act(self, action, page, text=None):
        previous_target = self.target
        self.follow_popup()
        if self.target != previous_target:
            raise StalePage("New child tab opened; observe it before another action")
        if not self.fresh(page, action):
            raise StalePage("Page changed since this decision")
        if action["kind"] == "wait":
            time.sleep(0.1)
        result = browser_operation(
            {"operation": "act", "session": self.session, "action": action, "text": text}
        )
        self.after_input = action if action["kind"] != "wait" else None
        return result

    def close(self):
        for target in self.owned_targets.copy():
            cdp("Target.closeTarget", targetId=target)
            self.owned_targets.discard(target)
        self.target = None


def fingerprint(state):
    content = {key: state[key] for key in ("url", "text", "actions", "scroll")}
    return hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()


def browser_operation(request):
    operation = request["operation"]
    session = request["session"]

    def call(method, **params):
        return cdp(method, session_id=session, **params)

    def evaluate(expression):
        result = call("Runtime.evaluate", expression=expression, returnByValue=True)
        if result.get("exceptionDetails"):
            if operation == "act" and request["action"]["kind"] == "select":
                raise RuntimeError("Dropdown execution was interrupted")
            raise StalePage("Document changed during evaluation")
        return result.get("result", {}).get("value")

    if operation == "act":
        action = request["action"]
        kind = action["kind"]
        if kind == "scroll":
            width, height = evaluate("[innerWidth,innerHeight]")
            call(
                "Input.dispatchMouseEvent",
                type="mouseWheel",
                x=width / 2,
                y=height * 0.7,
                deltaX=0,
                deltaY=action["delta"],
            )
        elif kind != "wait":
            if type(action["node"]) is not int:
                raise ValueError("Invalid observed node")
            target = evaluate(
                """(action => {
              const e=window.__jevFast?.nodes.get(action.node);
              if (!e?.isConnected || e.matches(':disabled') || e.closest('[aria-disabled="true"],[inert]') ||
                  !e.checkVisibility({checkOpacity:true,checkVisibilityCSS:true})) return null;
              if (action.kind==='fill' &&
                  (e.readOnly || e.getAttribute('aria-readonly')==='true')) return null;
              const r=e.getBoundingClientRect(), x=r.x+r.width/2, y=r.y+r.height/2;
              if (!r.width || !r.height || x<0 || y<0 || x>=innerWidth || y>=innerHeight) return null;
              if (!e.contains(document.elementFromPoint(x,y))) return null;
              if (action.kind==='select') {
                if (e.tagName!=='SELECT' || ![...e.options].some(o=>o.value===action.value &&
                    !o.disabled && !o.closest('optgroup[disabled]'))) return null;
                e.value=action.value;
                e.dispatchEvent(new Event('input',{bubbles:true}));
                e.dispatchEvent(new Event('change',{bubbles:true}));
              }
              return {x,y};
            })("""
                + json.dumps(action)
                + ")"
            )
            if target is None:
                if kind == "select":
                    raise RuntimeError("Dropdown execution was not confirmed")
                raise StalePage("Target changed or is covered")
            if kind != "select":
                x, y = target["x"], target["y"]
                for event in ("mousePressed", "mouseReleased"):
                    call("Input.dispatchMouseEvent", type=event, x=x, y=y, button="left", clickCount=1)
                if kind == "fill":
                    modifiers = 4 if sys.platform == "darwin" else 2
                    call(
                        "Input.dispatchKeyEvent",
                        type="keyDown",
                        key="a",
                        code="KeyA",
                        modifiers=modifiers,
                        commands=["selectAll"],
                    )
                    call(
                        "Input.dispatchKeyEvent",
                        type="keyUp",
                        key="a",
                        code="KeyA",
                        modifiers=modifiers,
                    )
                    call("Input.insertText", text=request["text"])
                elif kind == "press":
                    if action.get("key") != "Enter":
                        raise ValueError("Unsupported key")
                    call(
                        "Input.dispatchKeyEvent",
                        type="keyDown",
                        key="Enter",
                        code="Enter",
                        windowsVirtualKeyCode=13,
                        text="\r",
                    )
                    call(
                        "Input.dispatchKeyEvent",
                        type="keyUp",
                        key="Enter",
                        code="Enter",
                        windowsVirtualKeyCode=13,
                    )
        return {"executed": action["id"]}

    info = evaluate(READ_STATE)
    if info is None:
        raise StalePage("Document is navigating")
    info["fingerprint"] = fingerprint(info)
    return info
