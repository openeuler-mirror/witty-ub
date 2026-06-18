#include "urma_failure_139.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure139> g_urma("urma_139");

bool UrmaFailure139::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_create_pjfr") != std::string::npos &&
           message.find("Failed to create pjfr") != std::string::npos;
}

std::string UrmaFailure139::GetName() const
{
    return "下层资源创建失败导致创建物理JFR失败";
}

std::string UrmaFailure139::GetRootCauseDesc() const
{
    return "bondp_create_pjfr在创建物理JFR过程中依赖下层对象或provider创建结果，下层返回失败后当前资源无法建立。";
}

RootCause UrmaFailure139::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure139::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure139::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_create_pjfr，Failed to create pjfr。";
}

std::string UrmaFailure139::GetId() const
{
    return "urma_139";
}
} // namespace diag
