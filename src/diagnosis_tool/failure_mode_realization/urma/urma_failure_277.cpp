#include "urma_failure_277.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure277> g_urma("urma_277");

bool UrmaFailure277::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_log_set_thread_tag") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure277::GetName() const
{
    return "tag无效导致设置LOG、thread、TAG失败";
}

std::string UrmaFailure277::GetRootCauseDesc() const
{
    return "urma_log_set_thread_tag用于设置LOG、thread、TAG，调用方传入的tag不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure277::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure277::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure277::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_log_set_thread_tag，Invalid parameter.。";
}

std::string UrmaFailure277::GetId() const
{
    return "urma_277";
}
} // namespace diag
