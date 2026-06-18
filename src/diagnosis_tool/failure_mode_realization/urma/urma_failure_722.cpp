#include "urma_failure_722.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure722> g_urma("urma_722");

bool UrmaFailure722::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_set_jfr_opt") != std::string::npos &&
           message.find("Failed to exec urma_jfr_set_options.") != std::string::npos;
}

std::string UrmaFailure722::GetName() const
{
    return "设置JFR执行失败导致设置JFR失败";
}

std::string UrmaFailure722::GetRootCauseDesc() const
{
    return "urma_set_jfr_opt执行设置JFR时依赖的设置JFR步骤返回错误，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure722::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure722::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure722::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_set_jfr_opt，Failed to exec urma_jfr_set_options.。";
}

std::string UrmaFailure722::GetId() const
{
    return "urma_722";
}
} // namespace diag
