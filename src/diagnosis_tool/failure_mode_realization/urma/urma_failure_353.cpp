#include "urma_failure_353.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure353> g_urma("urma_353");

bool UrmaFailure353::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_create_pjfce") != std::string::npos &&
           message.find("Failed to create pjfce") != std::string::npos;
}

std::string UrmaFailure353::GetName() const
{
    return "下层资源创建失败导致创建物理JFCE失败";
}

std::string UrmaFailure353::GetRootCauseDesc() const
{
    return "bondp_create_pjfce在创建物理JFCE过程中依赖下层对象或provider创建结果，下层返回失败后当前资源无法建立。";
}

RootCause UrmaFailure353::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure353::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure353::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_create_pjfce，Failed to create pjfce。";
}

std::string UrmaFailure353::GetId() const
{
    return "urma_353";
}
} // namespace diag
