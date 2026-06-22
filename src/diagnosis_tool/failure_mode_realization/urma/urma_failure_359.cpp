#include "urma_failure_359.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure359> g_urma("urma_359");

bool UrmaFailure359::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_delete_jfce") != std::string::npos &&
           message.find("Failed to delete jfce[") != std::string::npos &&
           message.find("], still in use. use_cnt:") != std::string::npos;
}

std::string UrmaFailure359::GetName() const
{
    return "JFCE仍被引用导致删除JFCE失败";
}

std::string UrmaFailure359::GetRootCauseDesc() const
{
    return "bondp_delete_jfce在释放JFCE前检查到引用计数未清零，说明仍有上层对象或事件处理流程占用该资源。";
}

RootCause UrmaFailure359::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure359::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure359::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_delete_jfce，Failed to delete jfce[，], still in use. use_cnt:。";
}

std::string UrmaFailure359::GetId() const
{
    return "urma_359";
}
} // namespace diag
