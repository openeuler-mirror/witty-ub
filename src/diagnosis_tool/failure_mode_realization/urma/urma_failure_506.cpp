#include "urma_failure_506.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure506> g_urma("urma_506");

bool UrmaFailure506::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_delete_jfr") != std::string::npos &&
           message.find("Failed to delete jfr[") != std::string::npos &&
           message.find("], still in use. use_cnt:") != std::string::npos;
}

std::string UrmaFailure506::GetName() const
{
    return "JFR仍被引用导致删除JFR失败";
}

std::string UrmaFailure506::GetRootCauseDesc() const
{
    return "bondp_delete_jfr在释放JFR前检查到引用计数未清零，说明仍有上层对象或事件处理流程占用该资源。";
}

RootCause UrmaFailure506::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string UrmaFailure506::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure506::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_delete_jfr，Failed to delete jfr[，], still in use. use_cnt:。";
}

std::string UrmaFailure506::GetId() const
{
    return "urma_506";
}
} // namespace diag
