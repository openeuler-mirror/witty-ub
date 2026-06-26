#include "urma_failure_331.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure331> g_urma("urma_331");

bool UrmaFailure331::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_register_seg") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure331::GetName() const
{
    return "URMA context、dev_fd、tseg、配置参数无效导致注册Segment失败";
}

std::string UrmaFailure331::GetRootCauseDesc() const
{
    return "urma_cmd_register_seg用于注册Segment，调用方传入的URMA "
           "context、dev_fd、tseg、配置参数不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure331::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure331::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure331::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_register_seg，Invalid parameter。";
}

std::string UrmaFailure331::GetId() const
{
    return "urma_331";
}
} // namespace diag
