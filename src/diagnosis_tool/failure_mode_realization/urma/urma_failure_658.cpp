#include "urma_failure_658.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure658> g_urma("urma_658");

bool UrmaFailure658::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_parse_port_attr") != std::string::npos &&
           message.find("snprintf failed, path:") != std::string::npos &&
           message.find(", port_num:") != std::string::npos;
}

std::string UrmaFailure658::GetName() const
{
    return "解析端口、ATTR执行失败导致解析端口、ATTR失败";
}

std::string UrmaFailure658::GetRootCauseDesc() const
{
    return "urma_parse_port_attr执行解析端口、ATTR时依赖的解析端口、ATTR步骤返回错误，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure658::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure658::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure658::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_parse_port_attr，snprintf failed, path:，, port_num:。";
}

std::string UrmaFailure658::GetId() const
{
    return "urma_658";
}
} // namespace diag
