#include "urma_failure_335.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure335> g_urma("urma_335");

bool UrmaFailure335::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_import_seg") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure335::GetName() const
{
    return "URMA context、dev_fd、tseg、配置参数无效导致导入Segment失败";
}

std::string UrmaFailure335::GetRootCauseDesc() const
{
    return "urma_cmd_import_seg用于导入Segment，调用方传入的URMA "
           "context、dev_fd、tseg、配置参数不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure335::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure335::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure335::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_import_seg，Invalid parameter。";
}

std::string UrmaFailure335::GetId() const
{
    return "urma_335";
}
} // namespace diag
