#include "urma_failure_419.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure419> g_urma("urma_419");

bool UrmaFailure419::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_delete_jfc_batch") != std::string::npos &&
           message.find("bad jfc index exceed array length, bad_jfc_index:") != std::string::npos;
}

std::string UrmaFailure419::GetName() const
{
    return "JFC状态不满足要求导致删除JFC失败";
}

std::string UrmaFailure419::GetRootCauseDesc() const
{
    return "urma_cmd_delete_jfc_batch执行删除JFC时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure419::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure419::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure419::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_delete_jfc_batch，bad jfc index exceed array length, "
           "bad_jfc_index:。";
}

std::string UrmaFailure419::GetId() const
{
    return "urma_419";
}
} // namespace diag
