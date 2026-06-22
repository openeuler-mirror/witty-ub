#include "urma_failure_752.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure752> g_urma("urma_752");

bool UrmaFailure752::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_open_drivers") != std::string::npos &&
           message.find("Failed to prepare dli_fname.") != std::string::npos;
}

std::string UrmaFailure752::GetName() const
{
    return "打开drivers执行失败导致打开drivers失败";
}

std::string UrmaFailure752::GetRootCauseDesc() const
{
    return "urma_open_drivers执行打开drivers时依赖的打开drivers步骤返回错误，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure752::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure752::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure752::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_open_drivers，Failed to prepare dli_fname.。";
}

std::string UrmaFailure752::GetId() const
{
    return "urma_752";
}
} // namespace diag
