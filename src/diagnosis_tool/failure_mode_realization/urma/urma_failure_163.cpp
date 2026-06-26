#include "urma_failure_163.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure163> g_urma("urma_163");

bool UrmaFailure163::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_create_context") != std::string::npos &&
           message.find("Failed to create health check scene") != std::string::npos;
}

std::string UrmaFailure163::GetName() const
{
    return "下层资源创建失败导致创建context失败";
}

std::string UrmaFailure163::GetRootCauseDesc() const
{
    return "bondp_create_context在创建context过程中依赖下层对象或provider创建结果，下层返回失败后当前资源无法建立。";
}

RootCause UrmaFailure163::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure163::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure163::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_create_context，Failed to create health check scene。";
}

std::string UrmaFailure163::GetId() const
{
    return "urma_163";
}
} // namespace diag
