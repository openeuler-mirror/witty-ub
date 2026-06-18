#include "urma_failure_598.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure598> g_urma("urma_598");

bool UrmaFailure598::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_deactive_jetty") != std::string::npos &&
           message.find("Failed to exec ops->deactive_jetty.") != std::string::npos;
}

std::string UrmaFailure598::GetName() const
{
    return "去激活Jetty执行失败导致去激活Jetty失败";
}

std::string UrmaFailure598::GetRootCauseDesc() const
{
    return "urma_deactive_jetty执行去激活Jetty时依赖的去激活Jetty步骤返回错误，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure598::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure598::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure598::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_deactive_jetty，Failed to exec ops->deactive_jetty.。";
}

std::string UrmaFailure598::GetId() const
{
    return "urma_598";
}
} // namespace diag
