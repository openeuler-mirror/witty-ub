#include "urma_failure_204.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure204> g_urma("urma_204");

bool UrmaFailure204::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_add_jetty_to_jetty_grp") != std::string::npos &&
           message.find("failed to add jetty to jetty_grp.") != std::string::npos;
}

std::string UrmaFailure204::GetName() const
{
    return "添加Jetty、Jetty组执行失败导致添加Jetty、Jetty组失败";
}

std::string UrmaFailure204::GetRootCauseDesc() const
{
    return "urma_add_jetty_to_jetty_"
           "grp执行添加Jetty、Jetty组时依赖的添加Jetty、Jetty组步骤返回错误，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure204::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure204::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure204::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_add_jetty_to_jetty_grp，failed to add jetty to jetty_grp.。";
}

std::string UrmaFailure204::GetId() const
{
    return "urma_204";
}
} // namespace diag
