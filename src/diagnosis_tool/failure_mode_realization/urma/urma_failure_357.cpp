#include "urma_failure_357.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure357> g_urma("urma_357");

bool UrmaFailure357::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_create_jfce") != std::string::npos &&
           message.find("Failed to create vjfce.") != std::string::npos;
}

std::string UrmaFailure357::GetName() const
{
    return "下层资源创建失败导致创建JFCE失败";
}

std::string UrmaFailure357::GetRootCauseDesc() const
{
    return "bondp_create_jfce在创建JFCE过程中依赖下层对象或provider创建结果，下层返回失败后当前资源无法建立。";
}

RootCause UrmaFailure357::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure357::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure357::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_create_jfce，Failed to create vjfce.。";
}

std::string UrmaFailure357::GetId() const
{
    return "urma_357";
}
} // namespace diag
