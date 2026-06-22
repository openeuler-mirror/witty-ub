#include "urma_failure_714.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure714> g_urma("urma_714");

bool UrmaFailure714::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_active_jfs") != std::string::npos &&
           message.find("Invalid parameter, trans_mode:") != std::string::npos;
}

std::string UrmaFailure714::GetName() const
{
    return "JFS无效导致激活JFS失败";
}

std::string UrmaFailure714::GetRootCauseDesc() const
{
    return "urma_active_jfs用于激活JFS，调用方传入的JFS不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure714::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure714::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure714::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_active_jfs，Invalid parameter, trans_mode:。";
}

std::string UrmaFailure714::GetId() const
{
    return "urma_714";
}
} // namespace diag
