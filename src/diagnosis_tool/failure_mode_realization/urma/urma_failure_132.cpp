#include "urma_failure_132.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure132> g_urma("urma_132");

bool UrmaFailure132::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_create_pjfs") != std::string::npos &&
           message.find("Failed to create pjfs") != std::string::npos;
}

std::string UrmaFailure132::GetName() const
{
    return "下层资源创建失败导致创建物理JFS失败";
}

std::string UrmaFailure132::GetRootCauseDesc() const
{
    return "bondp_create_pjfs在创建物理JFS过程中依赖下层对象或provider创建结果，下层返回失败后当前资源无法建立。";
}

RootCause UrmaFailure132::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure132::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure132::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_create_pjfs，Failed to create pjfs。";
}

std::string UrmaFailure132::GetId() const
{
    return "urma_132";
}
} // namespace diag
