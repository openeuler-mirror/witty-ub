#include "urma_failure_148.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure148> g_urma("urma_148");

bool UrmaFailure148::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_create_jetty") != std::string::npos &&
           message.find("Failed to create bondp comp") != std::string::npos;
}

std::string UrmaFailure148::GetName() const
{
    return "下层资源创建失败导致创建Jetty失败";
}

std::string UrmaFailure148::GetRootCauseDesc() const
{
    return "bondp_create_jetty在创建Jetty过程中依赖下层对象或provider创建结果，下层返回失败后当前资源无法建立。";
}

RootCause UrmaFailure148::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure148::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure148::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_create_jetty，Failed to create bondp comp。";
}

std::string UrmaFailure148::GetId() const
{
    return "urma_148";
}
} // namespace diag
