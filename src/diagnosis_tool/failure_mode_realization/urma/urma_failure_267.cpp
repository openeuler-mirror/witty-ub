#include "urma_failure_267.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure267> g_urma("urma_267");

bool UrmaFailure267::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_get_net_addr_list") != std::string::npos &&
           message.find("Invalid parameter with max_netaddr_cnt as 0.") != std::string::npos;
}

std::string UrmaFailure267::GetName() const
{
    return "cnt、URMA context、URMA设备、设备sysfs信息无效导致获取NET、ADDR、列表失败";
}

std::string UrmaFailure267::GetRootCauseDesc() const
{
    return "urma_get_net_addr_list用于获取NET、ADDR、列表，调用方传入的cnt、URMA "
           "context、URMA设备、设备sysfs信息不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure267::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure267::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure267::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_get_net_addr_list，Invalid parameter with max_netaddr_cnt as 0.。";
}

std::string UrmaFailure267::GetId() const
{
    return "urma_267";
}
} // namespace diag
