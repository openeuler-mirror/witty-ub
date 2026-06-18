#include "urma_failure_364.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure364> g_urma("urma_364");

bool UrmaFailure364::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_create_jfc") != std::string::npos &&
           message.find("Failed to create pjfc") != std::string::npos;
}

std::string UrmaFailure364::GetName() const
{
    return "下层资源创建失败导致创建JFC失败";
}

std::string UrmaFailure364::GetRootCauseDesc() const
{
    return "bondp_create_jfc在创建JFC过程中依赖下层对象或provider创建结果，下层返回失败后当前资源无法建立。";
}

RootCause UrmaFailure364::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure364::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure364::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_create_jfc，Failed to create pjfc。";
}

std::string UrmaFailure364::GetId() const
{
    return "urma_364";
}
} // namespace diag
