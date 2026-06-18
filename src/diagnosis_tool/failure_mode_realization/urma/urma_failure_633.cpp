#include "urma_failure_633.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure633> g_urma("urma_633");

bool UrmaFailure633::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_get_net_addr_list") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure633::GetName() const
{
    return "URMA context、dev_fd、net_addr_info、cnt无效导致获取NET、ADDR失败";
}

std::string UrmaFailure633::GetRootCauseDesc() const
{
    return "urma_cmd_get_net_addr_list用于获取NET、ADDR，调用方传入的URMA "
           "context、dev_fd、net_addr_info、cnt不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure633::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure633::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure633::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_get_net_addr_list，Invalid parameter.。";
}

std::string UrmaFailure633::GetId() const
{
    return "urma_633";
}
} // namespace diag
