#include "urma_failure_212.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure212> g_urma("urma_212");

bool UrmaFailure212::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_create_jetty_grp") != std::string::npos &&
           message.find("max_jetty_in_jetty_grp") != std::string::npos && message.find("is err.") != std::string::npos;
}

std::string UrmaFailure212::GetName() const
{
    return "Jetty组状态不满足要求导致创建Jetty组失败";
}

std::string UrmaFailure212::GetRootCauseDesc() const
{
    return "urma_create_jetty_grp执行创建Jetty组时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure212::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure212::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure212::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_create_jetty_grp，max_jetty_in_jetty_grp，is err.。";
}

std::string UrmaFailure212::GetId() const
{
    return "urma_212";
}
} // namespace diag
