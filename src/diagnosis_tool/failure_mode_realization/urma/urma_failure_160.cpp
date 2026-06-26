#include "urma_failure_160.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure160> g_urma("urma_160");

bool UrmaFailure160::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_create_context") != std::string::npos &&
           message.find("Failed to create ctx") != std::string::npos;
}

std::string UrmaFailure160::GetName() const
{
    return "下层资源创建失败导致创建context失败";
}

std::string UrmaFailure160::GetRootCauseDesc() const
{
    return "bondp_create_context在创建context过程中依赖下层对象或provider创建结果，下层返回失败后当前资源无法建立。";
}

RootCause UrmaFailure160::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure160::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure160::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_create_context，Failed to create ctx。";
}

std::string UrmaFailure160::GetId() const
{
    return "urma_160";
}
} // namespace diag
