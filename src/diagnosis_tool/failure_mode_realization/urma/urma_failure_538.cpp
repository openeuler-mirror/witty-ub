#include "urma_failure_538.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure538> g_urma("urma_538");

bool UrmaFailure538::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_delete_jfr_batch") != std::string::npos &&
           message.find("jfr not from the same dev, cannot delete in a batch, index:") != std::string::npos;
}

std::string UrmaFailure538::GetName() const
{
    return "JFR状态不满足要求导致删除JFR失败";
}

std::string UrmaFailure538::GetRootCauseDesc() const
{
    return "urma_cmd_delete_jfr_batch执行删除JFR时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure538::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure538::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure538::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_delete_jfr_batch，jfr not from the same dev, cannot delete in "
           "a batch"
           ", index:。";
}

std::string UrmaFailure538::GetId() const
{
    return "urma_538";
}
} // namespace diag
