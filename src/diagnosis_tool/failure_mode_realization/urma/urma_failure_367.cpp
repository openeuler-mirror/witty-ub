#include "urma_failure_367.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure367> g_urma("urma_367");

bool UrmaFailure367::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_delete_jfc") != std::string::npos &&
           message.find("Failed to delete jfc[") != std::string::npos &&
           message.find("], still in use. use_cnt:") != std::string::npos;
}

std::string UrmaFailure367::GetName() const
{
    return "JFC仍被引用导致删除JFC失败";
}

std::string UrmaFailure367::GetRootCauseDesc() const
{
    return "bondp_delete_jfc在释放JFC前检查到引用计数未清零，说明仍有上层对象或事件处理流程占用该资源。";
}

RootCause UrmaFailure367::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure367::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure367::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_delete_jfc，Failed to delete jfc[，], still in use. use_cnt:。";
}

std::string UrmaFailure367::GetId() const
{
    return "urma_367";
}
} // namespace diag
