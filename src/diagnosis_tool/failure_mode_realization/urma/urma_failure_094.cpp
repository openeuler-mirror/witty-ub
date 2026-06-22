#include "urma_failure_094.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure094> g_urma("urma_094");

bool UrmaFailure094::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_exchange_tp_info") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure094::GetName() const
{
    return "URMA context、配置参数、peer_tp_handle、rx_psn无效导致exchange、TP失败";
}

std::string UrmaFailure094::GetRootCauseDesc() const
{
    return "urma_cmd_exchange_tp_info用于exchange、TP，调用方传入的URMA "
           "context、配置参数、peer_tp_handle、rx_psn不满足接口前置条件，函数无法继续执行"
           "。";
}

RootCause UrmaFailure094::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure094::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure094::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_exchange_tp_info，Invalid parameter.。";
}

std::string UrmaFailure094::GetId() const
{
    return "urma_094";
}
} // namespace diag
