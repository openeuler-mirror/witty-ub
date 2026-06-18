#include "urma_failure_526.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure526> g_urma("urma_526");

bool UrmaFailure526::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_delete_jfs_batch") != std::string::npos &&
           message.find("jfs not from the same dev, cannot delete in a batch, index:") != std::string::npos;
}

std::string UrmaFailure526::GetName() const
{
    return "JFS状态不满足要求导致删除JFS失败";
}

std::string UrmaFailure526::GetRootCauseDesc() const
{
    return "urma_cmd_delete_jfs_batch执行删除JFS时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure526::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure526::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure526::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_delete_jfs_batch，jfs not from the same dev, cannot delete in "
           "a batch"
           ", index:。";
}

std::string UrmaFailure526::GetId() const
{
    return "urma_526";
}
} // namespace diag
