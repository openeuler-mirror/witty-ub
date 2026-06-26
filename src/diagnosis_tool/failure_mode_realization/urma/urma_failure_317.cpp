#include "urma_failure_317.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure317> g_urma("urma_317");

bool UrmaFailure317::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_register_seg") != std::string::npos &&
           message.find("Failed to create vseg") != std::string::npos;
}

std::string UrmaFailure317::GetName() const
{
    return "下层资源创建失败导致注册Segment失败";
}

std::string UrmaFailure317::GetRootCauseDesc() const
{
    return "bondp_register_seg在注册Segment过程中依赖下层对象或provider创建结果，下层返回失败后当前资源无法建立。";
}

RootCause UrmaFailure317::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure317::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure317::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_register_seg，Failed to create vseg。";
}

std::string UrmaFailure317::GetId() const
{
    return "urma_317";
}
} // namespace diag
