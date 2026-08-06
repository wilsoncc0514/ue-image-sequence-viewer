"""Asynchronous image rendering, preloading and navigation mixin."""
from __future__ import annotations

import os
import queue
import tkinter as tk
from typing import Any, Iterable

from PIL import Image, ImageOps, ImageTk
from ui.styles import STYLE
from utils.logger import logger

from core.image_rendering import render_image_to_fit


class RenderControllerMixin:

    def _invalidate_preload(self) -> Any:
        self.preload_seq += 1

    def _invalidate_render(self) -> Any:
        self.render_seq += 1

    def _clear_render_queue(self) -> Any:
        while True:
            try:
                self.render_queue.get_nowait()
            except queue.Empty:
                break

    def _cancel_preload_submit_job(self) -> Any:
        if self._preload_submit_job:
            self.root.after_cancel(self._preload_submit_job)
            self._preload_submit_job = None

    def _cancel_slider_job(self) -> Any:
        if self._slider_job:
            self.root.after_cancel(self._slider_job)
            self._slider_job = None
        self._slider_pending_idx = None

    def on_slider_press(self, event: Any=None) -> Any:
        self._slider_is_dragging = True

    def on_slider_release(self, event: Any=None) -> Any:
        self.root.focus_set()
        self._slider_is_dragging = False
        self._cancel_slider_job()
        if not self.current_filepaths:
            return
        try:
            idx = int(float(self.slider.get()))
        except Exception:
            idx = self.current_idx
        if 0 <= idx < len(self.current_filepaths):
            self.update_image_index(idx, force=idx == self.current_idx)
            cw, ch = (self.canvas.winfo_width(), self.canvas.winfo_height())
            if cw > 1 and ch > 1:
                self._preload_nearby_frames(idx, cw, ch, self.dataset_id)

    def _clear_caches(self, clear_original: Any=False) -> Any:
        with self.cache_lock:
            self.render_cache.clear()
            self.preload_pending.clear()
            if clear_original:
                self.original_cache.clear()

    @staticmethod
    def _evict_lru(cache: Any, max_size: Any) -> Any:
        while len(cache) > max_size:
            cache.popitem(last=False)

    def _is_seq_layer_node(self, node_id: Any) -> Any:
        return node_id in self.seq_folder_nodes

    def _auto_expand_seq_node(self, node_id: Any) -> Any:
        if node_id and self._is_seq_layer_node(node_id):
            self.tree.item(node_id, open=True)

    @staticmethod
    def _is_text_input_widget(widget: Any) -> Any:
        if widget is None:
            return False
        try:
            return widget.winfo_class() in {'Entry', 'TEntry', 'Text', 'Spinbox', 'TSpinbox', 'Combobox', 'TCombobox'}
        except tk.TclError:
            return False

    def on_global_horizontal_key(self, event: Any, step: Any) -> Any:
        widget = event.widget if event is not None else self.root.focus_get()
        if self._is_text_input_widget(widget):
            return None
        self.step_frame(step)
        return 'break'

    def on_global_vertical_key(self, event: Any, step: Any) -> Any:
        if self.root.focus_get() == self.tree:
            return self.on_tree_vertical_key(event, step)
        self.step_group(step)
        return 'break'

    def on_tree_vertical_key(self, event: Any, step: Any) -> Any:
        selection = self.tree.selection()
        if not selection:
            return 'break'
        item = selection[0]
        if self._is_seq_layer_node(item):
            self.tree.item(item, open=True)
            children = self.tree.get_children(item)
            if step > 0 and children:
                self.tree.selection_set(children[0])
                self.tree.focus(children[0])
                self.tree.see(children[0])
            return 'break'
        parent = self.tree.parent(item)
        if parent and self._is_seq_layer_node(parent):
            siblings = list(self.tree.get_children(parent))
            try:
                pos = siblings.index(item)
            except ValueError:
                return 'break'
            target_pos = pos + step
            if 0 <= target_pos < len(siblings):
                target = siblings[target_pos]
                self.tree.selection_set(target)
                self.tree.focus(target)
                self.tree.see(target)
            elif step < 0:
                self.tree.selection_set(parent)
                self.tree.focus(parent)
                self.tree.see(parent)
            return 'break'
        children = self.tree.get_children(item)
        if step > 0 and children:
            self.tree.item(item, open=True)
            target = children[0]
            self.tree.selection_set(target)
            self.tree.focus(target)
            self.tree.see(target)
        return 'break'

    def step_frame(self, step: int) -> str | None:
        """Move one frame via keyboard without triggering duplicate slider callbacks."""
        if not self.current_filepaths:
            return None
        idx = self.current_idx + step
        if 0 <= idx < len(self.current_filepaths):
            self._cancel_slider_job()
            self._begin_keyboard_preview()
            self._programmatic_slider_update = True
            try:
                self.slider.set(idx)
            finally:
                self._programmatic_slider_update = False
            self.update_image_index(idx)
        return 'break'

    def _begin_keyboard_preview(self) -> None:
        """Enter a short-lived mode tuned for long-press arrow-key preview."""
        self._keyboard_preview_active = True
        self._slider_is_dragging = True
        if self._keyboard_preview_job:
            self.root.after_cancel(self._keyboard_preview_job)
        self._keyboard_preview_job = self.root.after(
            self.config.performance.keyboard_preview_settle_ms,
            self._end_keyboard_preview,
        )

    def _end_keyboard_preview(self) -> None:
        """Leave keyboard-preview mode and perform one deeper preload pass."""
        self._keyboard_preview_job = None
        self._keyboard_preview_active = False
        self._slider_is_dragging = False
        if self.current_filepaths and self.current_idx >= 0:
            cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
            if cw > 1 and ch > 1:
                self._preload_nearby_frames(self.current_idx, cw, ch, self.dataset_id)

    def step_group(self, step: Any) -> Any:
        sel = self.tree.selection()
        if not sel:
            return
        item = sel[0]
        target = self.tree.next(item) if step > 0 else self.tree.prev(item)
        if not target and step > 0:
            p = self.tree.parent(item)
            if p:
                target = self.tree.next(p)
        elif not target and step < 0:
            p = self.tree.parent(item)
            if p:
                target = p
        if target:
            self.tree.selection_set(target)
            self.tree.see(target)

    def on_canvas_resize(self, event: Any) -> Any:
        self.canvas.coords(self.txt_status, event.width / 2, event.height / 2)
        if hasattr(self, 'txt_seq_stats'):
            self.canvas.coords(self.txt_seq_stats, event.width - 18, 18)
        if hasattr(self, 'txt_cache_stats'):
            self.canvas.coords(self.txt_cache_stats, event.width - 18, event.height - 18)
        if self._resize_job:
            self.root.after_cancel(self._resize_job)
        self._resize_job = self.root.after(self.config.performance.resize_debounce_ms, self._on_resize_finished)

    def _on_resize_finished(self) -> Any:
        self._resize_job = None
        if not self.current_filepaths or self.current_idx < 0:
            return
        self._invalidate_preload()
        self._invalidate_render()
        self._cancel_preload_submit_job()
        self._clear_render_queue()
        self._clear_caches()
        self.update_image_index(self.current_idx, force=True)

    def on_slider_move(self, val: Any) -> None:
        if getattr(self, '_programmatic_slider_update', False):
            return
        idx = int(float(val))
        if idx == self.current_idx:
            return
        self._slider_pending_idx = idx
        if self._slider_job:
            self.root.after_cancel(self._slider_job)
        self._slider_job = self.root.after(self.config.performance.slider_debounce_ms, self._flush_slider_move)

    def _flush_slider_move(self) -> Any:
        self._slider_job = None
        if self._slider_pending_idx is not None:
            self.update_image_index(self._slider_pending_idx)
            self._slider_pending_idx = None

    def update_image_index(self, idx: Any, force: Any=False) -> Any:
        """切换当前帧。

        v2.22 关键优化：取消缩放功能后，主线程不再同步读取/缩放未缓存图片；
        同时通过更高并发 worker、方向预测预加载和更大的缓存窗口提高命中率。
        - 缓存命中：立即显示。
        - 缓存未命中：只更新文字与提交异步渲染请求，UI 不阻塞。
        - 缓存维度减少为 dataset/index/canvas size，拖动时更容易命中缓存。
        """
        if not self.current_filepaths:
            return
        if idx < 0 or idx >= len(self.current_filepaths):
            return
        if not force and idx == self.current_idx:
            return
        cw, ch = (self.canvas.winfo_width(), self.canvas.winfo_height())
        if cw <= 1 or ch <= 1:
            return
        previous_idx = self.current_idx
        if previous_idx >= 0 and idx != previous_idx:
            self.navigation_direction = 1 if idx > previous_idx else -1
            self._last_frame_idx_for_direction = previous_idx
        self.current_idx = idx
        dataset_id = self.dataset_id
        path = self.current_filepaths[idx]
        cache_key = (dataset_id, idx, cw, ch)
        self.lbl_filename.config(text=os.path.basename(path))
        self.lbl_counter.config(text=f'{idx + 1} / {len(self.current_filepaths)}')
        with self.cache_lock:
            cached = self.render_cache.pop(cache_key, None)
            if cached is not None:
                self.render_cache[cache_key] = cached
        if cached is not None:
            self._cache_render_hits += 1
            self._update_cache_stats_overlay()
            self._display_pil_image(cached, idx, cw, ch, dataset_id)
            self._preload_nearby_frames(idx, cw, ch, dataset_id)
            return
        self._cache_render_misses += 1
        self._update_cache_stats_overlay()
        self._show_canvas_status('')
        self._request_async_render(idx, path, cw, ch, dataset_id)
        self._preload_nearby_frames(idx, cw, ch, dataset_id)

    def _display_pil_image(self, img: Any, idx: Any, cw: Any, ch: Any, dataset_id: Any) -> Any:
        if self._closed or dataset_id != self.dataset_id or idx != self.current_idx:
            return
        self.current_tk_image = ImageTk.PhotoImage(img)
        self.canvas.coords(self.image_on_canvas, cw / 2, ch / 2)
        self.canvas.itemconfig(self.image_on_canvas, image=self.current_tk_image)
        self._show_canvas_status('')

    def _request_async_render(self, idx: Any, path: Any, cw: Any, ch: Any, dataset_id: Any) -> Any:
        self._invalidate_render()
        seq = self.render_seq
        request = (seq, dataset_id, idx, path, cw, ch)
        self._clear_render_queue()
        try:
            self.render_queue.put_nowait(request)
            self._kick_render_result_polling()
        except queue.Full:
            pass

    def _render_worker_loop(self) -> Any:
        while not self.render_stop_event.is_set():
            try:
                request = self.render_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            while True:
                try:
                    request = self.render_queue.get_nowait()
                except queue.Empty:
                    break
            seq, ds_id, idx, path, cw, ch = request
            if self._closed or self.render_seq != seq or self.dataset_id != ds_id:
                continue
            cache_key = (ds_id, idx, cw, ch)
            with self.cache_lock:
                cached = self.render_cache.pop(cache_key, None)
                if cached is not None:
                    self.render_cache[cache_key] = cached
            if cached is not None:
                self._schedule_render_finish(seq, ds_id, idx, cw, ch, cached, None)
                continue
            try:
                original = self._get_original_image(ds_id, idx, path)
                if original is None:
                    raise OSError(f'无法读取图片：{path}')
                img = self._render_image_to_fit(original, cw, ch)
                if self._closed or self.render_seq != seq or self.dataset_id != ds_id:
                    continue
                with self.cache_lock:
                    self.render_cache[cache_key] = img
                    self._evict_lru(self.render_cache, self.max_render_cache_size)
                self._schedule_render_finish(seq, ds_id, idx, cw, ch, img, None)
            except Exception as exc:
                logger.error(f'异步渲染失败: {path}', exc_info=True)
                self._schedule_render_finish(seq, ds_id, idx, cw, ch, None, exc)

    def _schedule_render_finish(self, seq: Any, ds_id: Any, idx: Any, cw: Any, ch: Any, img: Any, error: Any) -> Any:
        """Queue a render result for the Tk main thread.

        Tkinter calls are not thread-safe. v3.1 used ``root.after`` from the
        render worker; under heavy preload this could deadlock with cache locks
        on macOS/Tk. Workers now only put data into a plain queue, and the main
        thread drains it through ``_poll_render_results``.
        """
        if self._closed:
            return
        result = (seq, ds_id, idx, cw, ch, img, error)
        try:
            self.render_result_queue.put_nowait(result)
        except queue.Full:
            # The newest navigation request matters most. Drop one stale
            # result rather than letting a stalled Tk loop grow memory.
            try:
                self.render_result_queue.get_nowait()
            except queue.Empty:
                return
            try:
                self.render_result_queue.put_nowait(result)
            except queue.Full:
                logger.error("渲染结果队列仍为满，已丢弃过期结果")

    def _start_render_result_polling(self) -> None:
        """Start the main-thread render-result polling loop."""
        if self._closed:
            return
        self._schedule_render_result_poll(self.config.performance.render_result_poll_ms)

    def _kick_render_result_polling(self) -> None:
        """Reset idle backoff and schedule a near-term render-result poll.

        Called from the Tk main thread when a fresh render request is submitted.
        Workers still never call Tk; they only put completed results into the
        queue consumed by ``_poll_render_results``.
        """
        self._render_result_empty_streak = 0
        self._schedule_render_result_poll(self.config.performance.render_result_poll_ms)

    def _schedule_render_result_poll(self, delay_ms: int) -> None:
        """Schedule the render-result poll callback with one active timer."""
        if self._closed:
            return
        if self._render_result_poll_job:
            try:
                self.root.after_cancel(self._render_result_poll_job)
            except Exception:
                pass
        self._render_result_poll_job = self.root.after(max(1, int(delay_ms)), self._poll_render_results)

    def _poll_render_results(self) -> None:
        """Apply completed render results on the Tk main thread.

        Empty queues back off automatically to reduce idle Tk timer pressure.
        A new render request calls ``_kick_render_result_polling`` and restores
        the fast cadence.
        """
        self._render_result_poll_job = None
        if self._closed:
            return

        processed = 0
        batch_size = self.config.performance.render_result_poll_batch_size
        while processed < batch_size:
            try:
                seq, ds_id, idx, cw, ch, img, error = self.render_result_queue.get_nowait()
            except queue.Empty:
                break
            processed += 1
            self._finish_async_render(seq, ds_id, idx, cw, ch, img, error)

        if processed:
            self._render_result_empty_streak = 0
        else:
            self._render_result_empty_streak += 1

        if getattr(self, '_cache_stats_dirty', False):
            self._cache_stats_dirty = False
            self._update_cache_stats_overlay()

        if self._closed:
            return
        if processed:
            delay = self.config.performance.render_result_poll_ms
        elif self._render_result_empty_streak >= self.config.performance.render_result_empty_slowdown_after:
            delay = self.config.performance.render_result_poll_max_idle_ms
        else:
            delay = self.config.performance.render_result_poll_idle_ms
        self._schedule_render_result_poll(delay)

    def _finish_async_render(self, seq: Any, ds_id: Any, idx: Any, cw: Any, ch: Any, img: Any, error: Any) -> Any:
        if self._closed or self.render_seq != seq or self.dataset_id != ds_id or (idx != self.current_idx):
            return
        if error is not None or img is None:
            path = self.current_filepaths[idx] if 0 <= idx < len(self.current_filepaths) else ''
            self._show_canvas_status('图片读取失败', color=STYLE.colors.danger, animate=True)
            if path:
                self.lbl_filename.config(text=os.path.basename(path))
            return
        self._display_pil_image(img, idx, cw, ch, ds_id)
        self._preload_nearby_frames(idx, cw, ch, ds_id)

    def _get_original_image(self, dataset_id: Any, idx: Any, path: Any) -> Any:
        if self._closed:
            return None
        key = (dataset_id, idx)
        with self.cache_lock:
            cached = self.original_cache.pop(key, None)
            if cached is not None:
                self.original_cache[key] = cached
                self._cache_original_hits += 1
                self._cache_stats_dirty = True
                return cached
        self._cache_original_misses += 1
        self._cache_stats_dirty = True
        try:
            with Image.open(path) as im:
                width, height = im.size
                if width <= 0 or height <= 0:
                    raise ValueError(f"图片尺寸无效：{width}x{height}")
                pixels = width * height
                max_pixels = self.config.safety.max_image_pixels
                if pixels > max_pixels:
                    raise ValueError(f"图片像素超过上限：{pixels} > {max_pixels}")
                if im.mode not in ('RGB', 'RGBA'):
                    img = ImageOps.exif_transpose(im).convert('RGB')
                else:
                    img = ImageOps.exif_transpose(im).copy()
                if dataset_id == self.dataset_id:
                    with self.cache_lock:
                        self.original_cache[key] = img
                        self._evict_lru(self.original_cache, self.max_original_cache_size)
                return img
        except Exception:
            logger.error(f'读取图片失败: {path}', exc_info=True)
            return None

    def _preload_nearby_frames(self, center: int, cw: int, ch: int, ds_id: int) -> None:
        """Schedule preload tasks around ``center`` with mode-specific windows."""
        if self._closed:
            return
        self._cancel_preload_submit_job()
        seq = self.preload_seq
        fps = tuple(self.current_filepaths)
        if getattr(self, '_keyboard_preview_active', False):
            radius = self.config.performance.keyboard_preload_radius
            reverse_radius = self.config.performance.keyboard_reverse_radius
            delay = 0
        else:
            radius = self.drag_preload_radius if self._slider_is_dragging else self.preload_radius
            reverse_radius = radius // 2
            delay = self.config.performance.preload_delay_drag_ms if self._slider_is_dragging else self.config.performance.preload_delay_idle_ms
        direction = self.navigation_direction
        args = (center, seq, ds_id, fps, cw, ch, radius, direction, reverse_radius)
        self._preload_submit_job = self.root.after(delay, lambda: self._submit_preload_tasks(args))

    def _submit_preload_tasks(self, args: Any) -> Any:
        self._preload_submit_job = None
        if self._closed:
            return
        center, seq, ds_id, fps, cw, ch, radius, direction, reverse_radius = args
        total = len(fps)
        max_pending = getattr(self.config.performance, 'max_preload_pending_tasks', 512)
        for i in self._nearby_indices(center, total, radius, direction, reverse_radius):
            if self._closed or self.preload_seq != seq or self.dataset_id != ds_id:
                return
            rk = (ds_id, i, cw, ch)
            with self.cache_lock:
                if len(self.preload_pending) >= max_pending:
                    return
                if rk in self.render_cache or rk in self.preload_pending:
                    continue
                self.preload_pending.add(rk)
            try:
                self.executor.submit(self._preload_one_frame, seq, ds_id, i, fps[i], cw, ch, rk)
            except RuntimeError:
                with self.cache_lock:
                    self.preload_pending.discard(rk)
                return

    def _preload_one_frame(self, seq: Any, ds_id: Any, idx: Any, path: Any, cw: Any, ch: Any, rk: Any) -> Any:
        try:
            if self._closed or self.preload_seq != seq or self.dataset_id != ds_id:
                return
            with self.cache_lock:
                if rk in self.render_cache:
                    return
            orig = self._get_original_image(ds_id, idx, path)
            if orig is None:
                return
            img = self._render_image_to_fit(orig, cw, ch)
            if self._closed or self.preload_seq != seq or self.dataset_id != ds_id:
                return
            with self.cache_lock:
                if rk not in self.render_cache:
                    self.render_cache[rk] = img
                    self._evict_lru(self.render_cache, self.max_render_cache_size)
        except Exception:
            logger.error(f'预加载失败: {path}', exc_info=True)
        finally:
            with self.cache_lock:
                self.preload_pending.discard(rk)

    @staticmethod
    def _nearby_indices(c: int, t: int, r: int, direction: int = 0, reverse_radius: int | None = None) -> Iterable[int]:
        """Yield preload indices, prioritizing the likely browsing direction.

        ``direction`` controls which side receives the full radius. The opposite
        side receives ``reverse_radius``. Direction ``0`` keeps the historical
        balanced left/right interleaving.
        """
        if t <= 0 or c < 0 or c >= t or r < 0:
            return
        reverse = r // 2 if reverse_radius is None else max(0, reverse_radius)
        yield c

        if direction == 0:
            for offset in range(1, r + 1):
                if c + offset < t:
                    yield c + offset
                if c - offset >= 0:
                    yield c - offset
            return

        forward_limit = r if direction > 0 else reverse
        backward_limit = r if direction < 0 else reverse

        def yield_forward(limit: int) -> Iterable[int]:
            for offset in range(1, limit + 1):
                idx = c + offset
                if idx < t:
                    yield idx

        def yield_backward(limit: int) -> Iterable[int]:
            for offset in range(1, limit + 1):
                idx = c - offset
                if idx >= 0:
                    yield idx

        if direction > 0:
            yield from yield_forward(forward_limit)
            yield from yield_backward(backward_limit)
        else:
            yield from yield_backward(backward_limit)
            yield from yield_forward(forward_limit)

    def _update_cache_stats_overlay(self) -> None:
        """Update the optional cache/debug overlay."""
        if not getattr(self.config.performance, 'debug_cache_stats', False):
            if hasattr(self, 'txt_cache_stats'):
                self.canvas.itemconfig(self.txt_cache_stats, text='')
            return
        if not hasattr(self, 'txt_cache_stats'):
            return
        render_total = self._cache_render_hits + self._cache_render_misses
        original_total = self._cache_original_hits + self._cache_original_misses
        render_pct = int(self._cache_render_hits * 100 / render_total) if render_total else 0
        original_pct = int(self._cache_original_hits * 100 / original_total) if original_total else 0
        with self.cache_lock:
            pending = len(self.preload_pending)
            rendered = len(self.render_cache)
            originals = len(self.original_cache)
        text = (
            f'R hit {render_pct}%  O hit {original_pct}%\n'
            f'cache {rendered}/{self.max_render_cache_size}  orig {originals}/{self.max_original_cache_size}\n'
            f'pending {pending}  workers {self.preload_worker_count}'
        )
        self.canvas.itemconfig(self.txt_cache_stats, text=text)

    @staticmethod
    def _render_image_to_fit(img: Any, cw: Any, ch: Any) -> Any:
        return render_image_to_fit(img, cw, ch)
