#include "urma_failure_638.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure638> g_urma("urma_638");

bool UrmaFailure638::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_get_dmac") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure638::GetName() const
{
    return "URMA context、net_addr、mac无效导致获取DMAC失败";
}

std::string UrmaFailure638::GetRootCauseDesc() const
{
    return "urma_cmd_get_dmac用于获取DMAC，调用方传入的URMA "
           "context、net_addr、mac不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure638::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure638::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure638::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_get_dmac，Invalid parameter.。";
}

std::string UrmaFailure638::GetId() const
{
    return "urma_638";
}
} // namespace diag
