def xml2str_sorted(data):
    s = f"<{data.name}"
    if data.namespace:
        if not data.parent or data.parent.namespace!=data.namespace:
            if 'xmlns' not in data.attrs:
                s += f' xmlns="{data.namespace}"'
    for key in sorted(data.attrs.keys()):
        val = str(data.attrs[key])
        s += f' {key}="{val}"'

    s += ">"
    cnt = 0
    if data.kids:
        for a in data.kids:
            if (len(data.data)-1) >= cnt:
                s += data.data[cnt]
            s += a.__str__() if isinstance(a, str) else xml2str_sorted(a)
            cnt += 1
    if (len(data.data)-1) >= cnt:
        s += data.data[cnt]
    if not data.kids and s.endswith('>'):
        s = f'{s[:-1]} />'
    else:
        s += f"</{data.name}>"
    return s

