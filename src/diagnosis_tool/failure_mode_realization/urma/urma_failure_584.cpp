#include "urma_failure_584.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure584> g_urma("urma_584");

bool UrmaFailure584::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_deactive_jfr") != std::string::npos &&
           message.find("Failed to exec ops->deactive_jfr.") != std::string::npos;
}

std::string UrmaFailure584::GetName() const
{
    return "去激活JFR执行失败导致去激活JFR失败";
}

std::string UrmaFailure584::GetRootCauseDesc() const
{
    return "urma_deactive_jfr执行去激活JFR时依赖的去激活JFR步骤返回错误，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure584::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure584::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure584::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_deactive_jfr，Failed to exec ops->deactive_jfr.。";
}

std::string UrmaFailure584::GetId() const
{
    return "urma_584";
}
} // namespace diag
