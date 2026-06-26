#include "urma_failure_314.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure314> g_urma("urma_314");

bool UrmaFailure314::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_register_seg") != std::string::npos &&
           message.find("Invalid token id for register bondp seg") != std::string::npos;
}

std::string UrmaFailure314::GetName() const
{
    return "Segment状态不满足要求导致注册Segment失败";
}

std::string UrmaFailure314::GetRootCauseDesc() const
{
    return "bondp_register_seg执行注册Segment时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure314::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure314::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure314::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_register_seg，Invalid token id for register bondp seg。";
}

std::string UrmaFailure314::GetId() const
{
    return "urma_314";
}
} // namespace diag
