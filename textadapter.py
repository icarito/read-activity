import os
import logging
import gtk
import pango
import gobject
import threading

from sugar.graphics import style

PAGE_SIZE = 38


class TextViewer(gobject.GObject):

    __gsignals__ = {
        'zoom-changed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                ([int])),
        'page-changed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                ([int, int])),
        'selection-changed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                              ([])),
    }

    def setup(self, activity):
        activity._scrolled = gtk.ScrolledWindow()
        activity._scrolled.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        activity._scrolled.props.shadow_type = gtk.SHADOW_NONE

        self._scrolled = activity._scrolled

        self.textview = gtk.TextView()
        self.textview.set_editable(False)
        self.textview.set_cursor_visible(False)
        self.textview.set_left_margin(50)
        self.textview.set_right_margin(50)
        self.textview.set_wrap_mode(gtk.WRAP_WORD)
        activity._scrolled.add(self.textview)
        self.textview.show()
        activity._scrolled.show()
        activity._hbox.pack_start(activity._scrolled, expand=True, fill=True)

        self._font_size = style.zoom(10)
        self.font_desc = pango.FontDescription("sans %d" % self._font_size)
        self.textview.modify_font(self.font_desc)
        self._zoom = 100
        self.font_zoom_relation = self._zoom / self._font_size
        self._current_page = 0

    def load_document(self, file_path):
        self._etext_file = open(file_path.replace('file://', ''), 'r')

        self.page_index = [0]
        pagecount = 0
        linecount = 0
        while self._etext_file:
            line = self._etext_file.readline()
            if not line:
                break
            line_increment = (len(line) / 80) + 1
            linecount = linecount + line_increment
            if linecount >= PAGE_SIZE:
                position = self._etext_file.tell()
                self.page_index.append(position)
                linecount = 0
                pagecount = pagecount + 1
        self._pagecount = pagecount + 1
        self.set_current_page(0)

    def _show_page(self, page_number):
        position = self.page_index[page_number]
        self._etext_file.seek(position)
        linecount = 0
        label_text = '\n\n\n'
        while linecount < PAGE_SIZE:
            line = self._etext_file.readline()
            if not line:
                break
            else:
                label_text = label_text + unicode(line,  "iso-8859-1")
            line_increment = (len(line) / 80) + 1
            linecount = linecount + line_increment
        textbuffer = self.textview.get_buffer()
        label_text = label_text + '\n\n\n'
        textbuffer.set_text(label_text)

    def connect_page_changed_handler(self, handler):
        self.connect('page-changed', handler)

    def load_metadata(self, activity):
        pass

    def set_current_page(self, page):
        old_page = self._current_page
        self._current_page = page
        self._show_page(self._current_page)
        self.emit('page-changed', old_page, self._current_page)

    def scroll(self, direction, horizontal):
        v_adjustment = self._scrolled.get_vadjustment()
        if direction == gtk.SCROLL_PAGE_BACKWARD:
            if v_adjustment.value == v_adjustment.lower:
                self.previous_page()
                return
            if v_adjustment.value > v_adjustment.lower:
                new_value = v_adjustment.value - v_adjustment.step_increment
                if new_value < v_adjustment.lower:
                    new_value = v_adjustment.lower
                v_adjustment.value = new_value
        else:
            if v_adjustment.value == \
                    v_adjustment.upper - v_adjustment.page_size:
                self.next_page()
                return
            if v_adjustment.value < \
                    v_adjustment.upper - v_adjustment.page_size:
                new_value = v_adjustment.value + v_adjustment.step_increment
                if new_value > v_adjustment.upper - v_adjustment.page_size:
                    new_value = v_adjustment.upper - v_adjustment.page_size
                v_adjustment.value = new_value

    def previous_page(self):
        v_adjustment = self._scrolled.get_vadjustment()
        v_adjustment.value = v_adjustment.upper - v_adjustment.page_size
        self.set_current_page(self.get_current_page() - 1)

    def next_page(self):
        v_adjustment = self._scrolled.get_vadjustment()
        v_adjustment.value = v_adjustment.lower
        self.set_current_page(self.get_current_page() + 1)

    def get_current_page(self):
        return self._current_page

    def get_pagecount(self):
        return self._pagecount

    def update_toc(self, activity):
        pass

    def handle_link(self, link):
        pass

    def get_current_file(self):
        pass

    def update_metadata(self):
        pass

    def copy(self):
        pass

    def update_view_size(self, _scrolled):
        pass

    def find_set_highlight_search(self, True):
        pass

    def setup_find_job(self, text, _find_updated_cb):
        self._find_job = _JobFind(self._etext_file, start_page=0,
                n_pages=self._pagecount,
                text=text, case_sensitive=False)
        self._find_updated_handler = self._find_job.connect('updated',
                _find_updated_cb)
        return self._find_job, self._find_updated_handler

    def find_next(self):
        self._find_job.find_next()

    def find_previous(self):
        self._find_job.find_previous()

    def find_changed(self, job, page):
        self.set_current_page(job.get_page())
        self._show_found_text(job.get_founded_tuple())

    def _show_found_text(self, founded_tuple):
        textbuffer = self.textview.get_buffer()
        tag = textbuffer.create_tag()
        tag.set_property('weight', pango.WEIGHT_BOLD)
        tag.set_property('foreground', 'white')
        tag.set_property('background', 'black')
        iterStart = textbuffer.get_iter_at_offset(founded_tuple[1])
        iterEnd = textbuffer.get_iter_at_offset(founded_tuple[2])
        textbuffer.apply_tag(tag, iterStart, iterEnd)

    def get_zoom(self):
        return self.font_zoom_relation * self._font_size

    def connect_zoom_handler(self, handler):
        self._view_notify_zoom_handler = \
                self.connect('zoom-changed', handler)
        return self._view_notify_zoom_handler

    def set_zoom(self, value):
        self._zoom = value
        self._font_size = int(self._zoom / self.font_zoom_relation)
        self.font_desc.set_size(self._font_size * 1024)
        self.textview.modify_font(self.font_desc)

    def zoom_in(self):
        self._set_font_size(self._font_size + 1)

    def zoom_out(self):
        self._set_font_size(self._font_size - 1)

    def _set_font_size(self, size):
        self._font_size = size
        self.font_desc.set_size(self._font_size * 1024)
        self.textview.modify_font(self.font_desc)
        self._zoom = self.font_zoom_relation * self._font_size
        self.emit('zoom-changed', self._zoom)

    def zoom_to_width(self):
        pass

    def can_zoom_in(self):
        return True

    def can_zoom_out(self):
        return self._font_size > 1

    def can_zoom_to_width(self):
        return False

    def zoom_to_best_fit(self):
        return False

    def zoom_to_actual_size(self):
        return False


class _JobFind(gobject.GObject):

    __gsignals__ = {
        'updated': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ([])),
    }

    def __init__(self, text_file, start_page, n_pages, text, \
                case_sensitive=False):
        gobject.GObject.__init__(self)
        gtk.gdk.threads_init()

        self._finished = False
        self._text_file = text_file
        self._start_page = start_page
        self._n_pages = n_pages
        self._text = text
        self._case_sensitive = case_sensitive
        self.threads = []

        s_thread = _SearchThread(self)
        self.threads.append(s_thread)
        s_thread.start()

    def cancel(self):
        '''
        Cancels the search job
        '''
        for s_thread in self.threads:
            s_thread.stop()

    def is_finished(self):
        '''
        Returns True if the entire search job has been finished
        '''
        return self._finished

    def get_search_text(self):
        '''
        Returns the search text
        '''
        return self._text

    def get_case_sensitive(self):
        '''
        Returns True if the search is case-sensitive
        '''
        return self._case_sensitive

    def find_next(self):
        self.threads[-1].find_next()

    def find_previous(self):
        self.threads[-1].find_previous()

    def get_page(self):
        return self.threads[-1].get_page()

    def get_founded_tuple(self):
        return self.threads[-1].get_founded_tuple()


class _SearchThread(threading.Thread):

    def __init__(self, obj):
        threading.Thread.__init__(self)
        self.obj = obj
        self.stopthread = threading.Event()

    def _start_search(self):
        pagecount = 0
        linecount = 0
        charcount = 0
        self._found_records = []
        self._current_found_item = -1
        self.obj._text_file.seek(0)
        while self.obj._text_file:
            line = unicode(self.obj._text_file.readline(), "iso-8859-1")
            line_length = len(line)
            if not line:
                break
            line_increment = (len(line) / 80) + 1
            linecount = linecount + line_increment
            positions = self._allindices(line.lower(), self.obj._text.lower())
            for position in positions:
                found_pos = charcount + position + 3
                found_tuple = (pagecount, found_pos, \
                        len(self.obj._text) + found_pos)
                self._found_records.append(found_tuple)
                self._current_found_item = 0
            charcount = charcount + line_length
            if linecount >= PAGE_SIZE:
                linecount = 0
                charcount = 0
                pagecount = pagecount + 1
        if self._current_found_item == 0:
            self.current_found_tuple = \
                    self._found_records[self._current_found_item]
            self._page = self.current_found_tuple[0]

        gtk.gdk.threads_enter()
        self.obj._finished = True
        self.obj.emit('updated')
        gtk.gdk.threads_leave()

        return False

    def _allindices(self,  line, search, listindex=None,  offset=0):
        if listindex is None:
            listindex = []
        if (line.find(search) == -1):
            return listindex
        else:
            offset = line.index(search) + offset
            listindex.append(offset)
            line = line[(line.index(search) + 1):]
            return self._allindices(line, search, listindex, offset + 1)

    def run(self):
        self._start_search()

    def stop(self):
        self.stopthread.set()

    def find_next(self):
        self._current_found_item = self._current_found_item + 1
        if self._current_found_item >= len(self._found_records):
            self._current_found_item = len(self._found_records) - 1
        self.current_found_tuple =  \
                self._found_records[self._current_found_item]
        self._page = self.current_found_tuple[0]
        self.obj.emit('updated')

    def find_previous(self):
        self._current_found_item = self._current_found_item - 1
        if self._current_found_item <= 0:
            self._current_found_item = 0
        self.current_found_tuple = \
                self._found_records[self._current_found_item]
        self._page = self.current_found_tuple[0]
        self.obj.emit('updated')

    def get_page(self):
        return self._page

    def get_founded_tuple(self):
        return self.current_found_tuple
