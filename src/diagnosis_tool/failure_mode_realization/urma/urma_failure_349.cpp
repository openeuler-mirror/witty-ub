#include "urma_failure_349.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure349> g_urma("urma_349");

bool UrmaFailure349::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_register_seg") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure349::GetName() const
{
    return "URMA context、seg_cfg、va无效导致注册Segment失败";
}

std::string UrmaFailure349::GetRootCauseDesc() const
{
    return "urma_register_seg用于注册Segment，调用方传入的URMA "
           "context、seg_cfg、va不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure349::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure349::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure349::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_register_seg，Invalid parameter.。";
}

std::string UrmaFailure349::GetId() const
{
    return "urma_349";
}
} // namespace diag
