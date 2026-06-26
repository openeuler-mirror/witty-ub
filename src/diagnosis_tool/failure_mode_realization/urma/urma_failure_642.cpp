#include "urma_failure_642.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure642> g_urma("urma_642");

bool UrmaFailure642::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_set_jetty_opt") != std::string::npos &&
           message.find("UB dev should use share jfr!") != std::string::npos;
}

std::string UrmaFailure642::GetName() const
{
    return "Jetty状态不满足要求导致设置Jetty失败";
}

std::string UrmaFailure642::GetRootCauseDesc() const
{
    return "urma_set_jetty_opt执行设置Jetty时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure642::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure642::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure642::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_set_jetty_opt，UB dev should use share jfr!。";
}

std::string UrmaFailure642::GetId() const
{
    return "urma_642";
}
} // namespace diag
