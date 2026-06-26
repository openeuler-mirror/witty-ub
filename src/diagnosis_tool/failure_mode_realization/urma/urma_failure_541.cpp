#include "urma_failure_541.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure541> g_urma("urma_541");

bool UrmaFailure541::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_delete_jfr_batch") != std::string::npos &&
           message.find("bad jfr index exceed array length, bad_jfr_index:") != std::string::npos;
}

std::string UrmaFailure541::GetName() const
{
    return "JFR状态不满足要求导致删除JFR失败";
}

std::string UrmaFailure541::GetRootCauseDesc() const
{
    return "urma_cmd_delete_jfr_batch执行删除JFR时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure541::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure541::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure541::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_delete_jfr_batch，bad jfr index exceed array length, "
           "bad_jfr_index:。";
}

std::string UrmaFailure541::GetId() const
{
    return "urma_541";
}
} // namespace diag
