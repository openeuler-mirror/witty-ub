#include "urma_failure_474.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure474> g_urma("urma_474");

bool UrmaFailure474::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_active_jfs") != std::string::npos &&
           message.find("jfs or jfc state is wrong in active_jfs.") != std::string::npos;
}

std::string UrmaFailure474::GetName() const
{
    return "JFS状态不满足要求导致激活JFS失败";
}

std::string UrmaFailure474::GetRootCauseDesc() const
{
    return "urma_active_jfs执行激活JFS时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure474::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure474::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure474::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_active_jfs，jfs or jfc state is wrong in active_jfs.。";
}

std::string UrmaFailure474::GetId() const
{
    return "urma_474";
}
} // namespace diag
