#include "urma_failure_142.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure142> g_urma("urma_142");

bool UrmaFailure142::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_create_jfr") != std::string::npos &&
           message.find("Failed to create vjfr") != std::string::npos;
}

std::string UrmaFailure142::GetName() const
{
    return "下层资源创建失败导致创建JFR失败";
}

std::string UrmaFailure142::GetRootCauseDesc() const
{
    return "bondp_create_jfr在创建JFR过程中依赖下层对象或provider创建结果，下层返回失败后当前资源无法建立。";
}

RootCause UrmaFailure142::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure142::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure142::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_create_jfr，Failed to create vjfr。";
}

std::string UrmaFailure142::GetId() const
{
    return "urma_142";
}
} // namespace diag
