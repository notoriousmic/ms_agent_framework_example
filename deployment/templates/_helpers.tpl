{{- define "labels"}}
    app.kubernetes.io/name: {{  .Values.app_name }}
    app.kubernetes.io/instance: {{ .Values.app_name }}
    app: {{  .Values.app_name }}
    {{- if .Values.orgLabel }}
    ou: {{ .Values.orgLabel }}
    {{- end }}
{{- end }}