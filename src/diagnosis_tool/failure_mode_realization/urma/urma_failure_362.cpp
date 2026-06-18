#include "urma_failure_362.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure362> g_urma("urma_362");

bool UrmaFailure362::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_create_pjfc") != std::string::npos &&
           message.find("Failed to create pjfc") != std::string::npos;
}

std::string UrmaFailure362::GetName() const
{
    return "下层资源创建失败导致创建物理JFC失败";
}

std::string UrmaFailure362::GetRootCauseDesc() const
{
    return "bondp_create_pjfc在创建物理JFC过程中依赖下层对象或provider创建结果，下层返回失败后当前资源无法建立。";
}

RootCause UrmaFailure362::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure362::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure362::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_create_pjfc，Failed to create pjfc。";
}

std::string UrmaFailure362::GetId() const
{
    return "urma_362";
}
} // namespace diag
