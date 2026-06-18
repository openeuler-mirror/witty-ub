#include "urma_failure_511.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure511> g_urma("urma_511");

bool UrmaFailure511::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_delete_jetty") != std::string::npos &&
           message.find("Failed to delete jetty[") != std::string::npos &&
           message.find("], still in use. use_cnt:") != std::string::npos;
}

std::string UrmaFailure511::GetName() const
{
    return "Jetty仍被引用导致删除Jetty失败";
}

std::string UrmaFailure511::GetRootCauseDesc() const
{
    return "bondp_delete_jetty在释放Jetty前检查到引用计数未清零，说明仍有上层对象或事件处理流程占用该资源。";
}

RootCause UrmaFailure511::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure511::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure511::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_delete_jetty，Failed to delete jetty[，], still in use. "
           "use_cnt:。";
}

std::string UrmaFailure511::GetId() const
{
    return "urma_511";
}
} // namespace diag
