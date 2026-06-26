#include "urma_failure_350.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure350> g_urma("urma_350");

bool UrmaFailure350::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_unregister_seg") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure350::GetName() const
{
    return "target_seg、URMA context、URMA设备无效导致注销Segment失败";
}

std::string UrmaFailure350::GetRootCauseDesc() const
{
    return "urma_unregister_seg用于注销Segment，调用方传入的target_seg、URMA "
           "context、URMA设备不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure350::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure350::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure350::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_unregister_seg，Invalid parameter.。";
}

std::string UrmaFailure350::GetId() const
{
    return "urma_350";
}
} // namespace diag
