#include "urma_failure_491.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure491> g_urma("urma_491");

bool UrmaFailure491::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_rearm_jfc") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure491::GetName() const
{
    return "dp_ops、rearm_jfc、urma_dev无效导致rearmrearm、JFC失败";
}

std::string UrmaFailure491::GetRootCauseDesc() const
{
    return "urma_rearm_jfc用于rearmrearm、JFC，调用方传入的dp_ops、rearm_jfc、urma_"
           "dev不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure491::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure491::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure491::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_rearm_jfc，Invalid parameter.。";
}

std::string UrmaFailure491::GetId() const
{
    return "urma_491";
}
} // namespace diag
