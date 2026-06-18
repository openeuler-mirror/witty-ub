#include "urma_failure_416.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure416> g_urma("urma_416");

bool UrmaFailure416::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_delete_jfc_batch") != std::string::npos &&
           message.find("jfc not from the same dev, cannot delete in a batch, index:") != std::string::npos;
}

std::string UrmaFailure416::GetName() const
{
    return "JFC状态不满足要求导致删除JFC失败";
}

std::string UrmaFailure416::GetRootCauseDesc() const
{
    return "urma_cmd_delete_jfc_batch执行删除JFC时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure416::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure416::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure416::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_delete_jfc_batch，jfc not from the same dev, cannot delete in "
           "a batch"
           ", index:。";
}

std::string UrmaFailure416::GetId() const
{
    return "urma_416";
}
} // namespace diag
