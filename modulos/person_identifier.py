import cv2
import numpy as np


class PersonAppearanceTracker:
    """Tracker simple por apariencia para re-identificar personas usando histograma de color."""

    def __init__(self, max_age=12, distance_threshold=120, appearance_threshold=0.75):
        self.max_age = max_age
        self.distance_threshold = distance_threshold
        self.appearance_threshold = appearance_threshold
        self.next_id = 1
        self.tracks = []

    def _clip_bbox(self, bbox, shape):
        h, w = shape[:2]
        x1 = max(0, int(round(bbox[0])))
        y1 = max(0, int(round(bbox[1])))
        x2 = min(w, int(round(bbox[2])))
        y2 = min(h, int(round(bbox[3])))
        if x2 <= x1 or y2 <= y1:
            return None
        return (x1, y1, x2, y2)

    def _extract_roi(self, frame, bbox):
        clipped = self._clip_bbox(bbox, frame.shape)
        if clipped is None:
            return None
        x1, y1, x2, y2 = clipped
        roi = frame[y1:y2, x1:x2]
        if roi.size == 0:
            return None

        pad = max(4, int(min(roi.shape[0], roi.shape[1]) * 0.08))
        x1p = max(0, x1 - pad)
        y1p = max(0, y1 - pad)
        x2p = min(frame.shape[1], x2 + pad)
        y2p = min(frame.shape[0], y2 + pad)
        roi = frame[y1p:y2p, x1p:x2p]
        if roi.size == 0:
            return None
        return roi

    def _compute_descriptor(self, frame, bbox):
        roi = self._extract_roi(frame, bbox)
        if roi is None:
            return None

        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        hist = cv2.calcHist([hsv], [0, 1, 2], None, [8, 8, 8], [0, 180, 0, 256, 0, 256])
        hist = cv2.normalize(hist, hist).flatten()
        return hist.astype(np.float32)

    def _hist_distance(self, a, b):
        if a is None or b is None:
            return 1.0
        return float(np.linalg.norm(a - b))

    def _center(self, bbox):
        return ((bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0)

    def _distance(self, p1, p2):
        return float(np.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2))

    def update(self, detections, frame):
        detections = list(detections)
        if frame is None:
            return []

        for track in self.tracks:
            track['age'] += 1
            if track['age'] > self.max_age:
                track['active'] = False

        active_tracks = [t for t in self.tracks if t.get('active', True)]
        assigned_tracks = set()
        assigned_dets = set()
        matched = []

        if active_tracks and detections:
            candidates = []
            for det_idx, det in enumerate(detections):
                bbox = det['bbox']
                center = self._center(bbox)
                desc = self._compute_descriptor(frame, bbox)
                for track_idx, track in enumerate(active_tracks):
                    if track_idx in assigned_tracks:
                        continue
                    dist = self._distance(center, track['center'])
                    desc_dist = self._hist_distance(desc, track['descriptor'])
                    score = dist / self.distance_threshold + desc_dist / self.appearance_threshold
                    candidates.append((score, track_idx, det_idx))

            candidates.sort(key=lambda x: x[0])
            for score, track_idx, det_idx in candidates:
                if score > 1.4:
                    continue
                if track_idx in assigned_tracks or det_idx in assigned_dets:
                    continue
                assigned_tracks.add(track_idx)
                assigned_dets.add(det_idx)
                matched.append((track_idx, det_idx))

        outputs = []
        for track_idx, det_idx in matched:
            track = active_tracks[track_idx]
            det = detections[det_idx]
            bbox = det['bbox']
            center = self._center(bbox)
            desc = self._compute_descriptor(frame, bbox)
            if desc is not None:
                if track['descriptor'] is None:
                    track['descriptor'] = desc
                else:
                    track['descriptor'] = 0.7 * track['descriptor'] + 0.3 * desc
            track['bbox'] = bbox
            track['center'] = center
            track['last_seen'] = self._frame_id if hasattr(self, '_frame_id') else 0
            track['age'] = 0
            track['active'] = True
            outputs.append({
                'tracking_id': track['tracking_id'],
                'bbox': bbox,
                'center': center,
                'descriptor': track['descriptor']
            })

        for det_idx, det in enumerate(detections):
            if det_idx in assigned_dets:
                continue
            bbox = det['bbox']
            center = self._center(bbox)
            desc = self._compute_descriptor(frame, bbox)
            track = {
                'tracking_id': self.next_id,
                'bbox': bbox,
                'center': center,
                'descriptor': desc,
                'last_seen': self._frame_id if hasattr(self, '_frame_id') else 0,
                'age': 0,
                'active': True
            }
            self.next_id += 1
            self.tracks.append(track)
            outputs.append({
                'tracking_id': track['tracking_id'],
                'bbox': bbox,
                'center': center,
                'descriptor': desc
            })

        self.tracks = [t for t in self.tracks if t.get('active', True)]
        return outputs

    def set_frame_id(self, frame_id):
        self._frame_id = frame_id
