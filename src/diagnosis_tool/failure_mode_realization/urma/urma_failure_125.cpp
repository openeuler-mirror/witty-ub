#include "urma_failure_125.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure125> g_urma("urma_125");

bool UrmaFailure125::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_modify_tp") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure125::GetName() const
{
    return "TP无效导致修改TP失败";
}

std::string UrmaFailure125::GetRootCauseDesc() const
{
    return "urma_modify_tp用于修改TP，调用方传入的TP不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure125::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure125::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure125::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_modify_tp，Invalid parameter.。";
}

std::string UrmaFailure125::GetId() const
{
    return "urma_125";
}
} // namespace diag
