#include "urma_failure_370.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure370> g_urma("urma_370");

bool UrmaFailure370::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_rearm_jfc") != std::string::npos &&
           message.find("Failed to rearm jfc: JFCE is NULL") != std::string::npos;
}

std::string UrmaFailure370::GetName() const
{
    return "rearmrearm、JFC执行失败导致rearmrearm、JFC失败";
}

std::string UrmaFailure370::GetRootCauseDesc() const
{
    return "bondp_rearm_jfc执行rearmrearm、JFC时依赖的rearmrearm、JFC步骤返回错误，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure370::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure370::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure370::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_rearm_jfc，Failed to rearm jfc: JFCE is NULL。";
}

std::string UrmaFailure370::GetId() const
{
    return "urma_370";
}
} // namespace diag
