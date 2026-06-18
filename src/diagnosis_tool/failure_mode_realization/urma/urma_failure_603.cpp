#include "urma_failure_603.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure603> g_urma("urma_603");

bool UrmaFailure603::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_delete_jetty_grp") != std::string::npos &&
           message.find("jetty grp in use, jetty_cnt:") != std::string::npos;
}

std::string UrmaFailure603::GetName() const
{
    return "Jetty组仍被引用导致删除Jetty组失败";
}

std::string UrmaFailure603::GetRootCauseDesc() const
{
    return "urma_delete_jetty_grp在释放Jetty组前检查到引用计数未清零，说明仍有上层对象或事件处理流程占用该资源。";
}

RootCause UrmaFailure603::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure603::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure603::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_delete_jetty_grp，jetty grp in use, jetty_cnt:。";
}

std::string UrmaFailure603::GetId() const
{
    return "urma_603";
}
} // namespace diag
