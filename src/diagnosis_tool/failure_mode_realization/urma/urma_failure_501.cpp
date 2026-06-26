#include "urma_failure_501.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure501> g_urma("urma_501");

bool UrmaFailure501::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_delete_jfs") != std::string::npos &&
           message.find("Failed to delete jfs[") != std::string::npos &&
           message.find("], still in use. use_cnt:") != std::string::npos;
}

std::string UrmaFailure501::GetName() const
{
    return "JFS仍被引用导致删除JFS失败";
}

std::string UrmaFailure501::GetRootCauseDesc() const
{
    return "bondp_delete_jfs在释放JFS前检查到引用计数未清零，说明仍有上层对象或事件处理流程占用该资源。";
}

RootCause UrmaFailure501::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure501::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure501::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_delete_jfs，Failed to delete jfs[，], still in use. use_cnt:。";
}

std::string UrmaFailure501::GetId() const
{
    return "urma_501";
}
} // namespace diag
