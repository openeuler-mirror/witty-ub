#include "urma_failure_061.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure061> g_urma("urma_061");

bool UrmaFailure061::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_unbind_jetty") != std::string::npos &&
           message.find("Failed to unbind tjetty [") != std::string::npos && message.find("](") != std::string::npos &&
           message.find(",") != std::string::npos && message.find(")") != std::string::npos;
}

std::string UrmaFailure061::GetName() const
{
    return "解绑Jetty执行失败导致解绑Jetty失败";
}

std::string UrmaFailure061::GetRootCauseDesc() const
{
    return "bondp_unbind_jetty执行解绑Jetty时依赖的解绑Jetty步骤返回错误，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure061::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure061::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure061::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_unbind_jetty，Failed to unbind tjetty [，](，,，)。";
}

std::string UrmaFailure061::GetId() const
{
    return "urma_061";
}
} // namespace diag
