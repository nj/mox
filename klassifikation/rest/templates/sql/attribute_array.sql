        ARRAY[
        {% for attribute_value in attribute_periods -%}
        ROW({% for value in attribute_value -%}
            {% if loop.last -%}
            ROW(
                '[{{ value.from }}, {{ value.to }})',
            {{ value.aktoerref|adapt }},
            {{ value.aktoertypekode|adapt }},
            {{ value.notetekst|adapt }}
        ) :: Virkning
            {% else -%}
            {% if value != None -%}
            {{ value|adapt }},
            {% else -%}
            NULL,
            {% endif -%}
            {% endif -%}
            {% endfor -%}
        ){% if not loop.last %},{% endif %}
        {% endfor -%}
    ] :: {{ attribute_name }}AttrType[]
