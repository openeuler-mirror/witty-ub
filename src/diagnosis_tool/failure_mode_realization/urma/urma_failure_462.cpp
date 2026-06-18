#include "urma_failure_462.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure462> g_urma("urma_462");

bool UrmaFailure462::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_set_jfc_opt") != std::string::npos &&
           message.find("Failed to exec ops->set_jfc_opt.") != std::string::npos;
}

std::string UrmaFailure462::GetName() const
{
    return "设置JFC执行失败导致设置JFC失败";
}

std::string UrmaFailure462::GetRootCauseDesc() const
{
    return "urma_set_jfc_opt执行设置JFC时依赖的设置JFC步骤返回错误，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure462::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure462::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure462::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_set_jfc_opt，Failed to exec ops->set_jfc_opt.。";
}

std::string UrmaFailure462::GetId() const
{
    return "urma_462";
}
} // namespace diag
