#ifndef ${header_name}
#define ${header_name}

#include "Gadgetron.h"

<%
    defined_names = []
%>
<%def name="list_of_arg_names(args)">\
<%
    result = []
    for a in args:
        if a.preprocess == "define":
            result.append(a.name)
        elif a.preprocess == "factory":
            if a.type == "pointer":
                result.append("&" + a.name)
            elif a.type == "object":
                result.append(a.name)
        else:
            result.append(a.value)
%>\
${",".join(result)}\
</%def>\
<%def name="preprocess(arg)">\
    % if arg.preprocess == "define":
        % if arg.name not in defined_names:
#define ${arg.name} ${arg.value}\
        <%
            defined_names.append(arg.name)
        %>\
        % endif
    % elif arg.preprocess == "factory":
        % if len(arg.sub_args) == 0:
${arg.class_name} ${arg.name} = ${arg.factory_method}();
        % else:
            % for a in arg.sub_args:
${preprocess(arg=a)}
            % endfor
${arg.class_name} ${arg.name} = ${arg.factory_method}(${list_of_arg_names(args=arg.sub_args)});
        % endif
    % endif
</%def>\
<%def name="declare(c)">\
    % if len(c.args) == 0:
${c.class_name} ${c.var_name};
    % else:
${c.class_name} ${c.var_name}(${list_of_arg_names(args=c.args)});
    % endif
</%def>\
% for c in components:
% for a in c.args:
${preprocess(arg=a)}
% endfor
${declare(c=c)}
% endfor

#endif