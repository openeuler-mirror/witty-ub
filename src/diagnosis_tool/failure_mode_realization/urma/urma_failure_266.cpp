#include "urma_failure_266.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure266> g_urma("urma_266");

bool UrmaFailure266::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_get_net_addr_list") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure266::GetName() const
{
    return "provider未提供get_tpn操作实现无效导致获取NET、ADDR、列表失败";
}

std::string UrmaFailure266::GetRootCauseDesc() const
{
    return "urma_get_net_addr_list用于获取NET、ADDR、列表，调用方传入的provider未提供get_"
           "tpn操作实现不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure266::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure266::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure266::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_get_net_addr_list，Invalid parameter.。";
}

std::string UrmaFailure266::GetId() const
{
    return "urma_266";
}
} // namespace diag
