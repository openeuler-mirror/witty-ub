#include "urma_failure_034.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure034> g_urma("urma_034");

bool UrmaFailure034::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bdp_slide_wnd_init") != std::string::npos &&
           message.find("Failed to init bitmap") != std::string::npos;
}

std::string UrmaFailure034::GetName() const
{
    return "初始化BDP、slide、WND执行失败导致初始化BDP、slide、WND失败";
}

std::string UrmaFailure034::GetRootCauseDesc() const
{
    return "bdp_slide_wnd_"
           "init执行初始化BDP、slide、WND时依赖的初始化BDP、slide、WND步骤返回错误，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure034::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure034::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure034::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bdp_slide_wnd_init，Failed to init bitmap。";
}

std::string UrmaFailure034::GetId() const
{
    return "urma_034";
}
} // namespace diag
