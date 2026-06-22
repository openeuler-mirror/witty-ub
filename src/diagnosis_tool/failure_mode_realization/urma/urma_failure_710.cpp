#include "urma_failure_710.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure710> g_urma("urma_710");

bool UrmaFailure710::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_set_jfs_opt") != std::string::npos &&
           message.find("invalid opt id or opt len") != std::string::npos;
}

std::string UrmaFailure710::GetName() const
{
    return "JFS状态不满足要求导致设置JFS失败";
}

std::string UrmaFailure710::GetRootCauseDesc() const
{
    return "urma_set_jfs_opt执行设置JFS时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure710::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure710::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure710::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_set_jfs_opt，invalid opt id or opt len。";
}

std::string UrmaFailure710::GetId() const
{
    return "urma_710";
}
} // namespace diag
